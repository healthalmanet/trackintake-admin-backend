import re
from django.db import connection

GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}


def normalize_email(email):
    return str(email or "").strip().lower()


def canonicalize_email(email):
    norm = normalize_email(email)
    if "@" not in norm:
        return norm
    local, domain = norm.rsplit("@", 1)
    if domain in GMAIL_DOMAINS:
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


def normalize_phone(phone):
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) < 7:
        return "", ""
    last10 = digits[-10:] if len(digits) >= 10 else ""
    return digits, last10


def sync_user_block_state(user_id, is_active, reason=""):
    """
    Keep user_user blocking columns and user_blockedcontact table in sync
    whenever an admin blocks, deactivates, or unblocks a user.
    """
    is_blocked = not bool(is_active)
    reason_text = str(reason or "").strip()

    with connection.cursor() as cursor:
        # Update blocking fields on user_user if columns exist
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'user_user'
              AND column_name IN ('is_blocked', 'blocked_reason', 'blocked_at');
            """
        )
        cols = {row[0] for row in cursor.fetchall()}
        if {"is_blocked", "blocked_reason", "blocked_at"}.issubset(cols):
            if is_blocked:
                cursor.execute(
                    """
                    UPDATE user_user
                    SET is_blocked = true,
                        blocked_reason = COALESCE(NULLIF(%s, ''), blocked_reason, 'Blocked by administrator'),
                        blocked_at = COALESCE(blocked_at, NOW())
                    WHERE id = %s;
                    """,
                    [reason_text, user_id],
                )
            else:
                cursor.execute(
                    """
                    UPDATE user_user
                    SET is_blocked = false,
                        blocked_reason = '',
                        blocked_at = NULL
                    WHERE id = %s;
                    """,
                    [user_id],
                )

        # Check if user_blockedcontact table exists
        cursor.execute("SELECT to_regclass('public.user_blockedcontact');")
        if not cursor.fetchone()[0]:
            return

        cursor.execute(
            "SELECT email, phone_number FROM user_user WHERE id = %s;",
            [user_id],
        )
        user_row = cursor.fetchone()
        if not user_row:
            return

        norm_email = normalize_email(user_row[0])
        canon_email = canonicalize_email(norm_email) if norm_email else ""

        if not is_blocked:
            cursor.execute(
                """
                UPDATE user_blockedcontact
                SET is_active = false, updated_at = NOW()
                WHERE is_active = true AND (user_id = %s OR (%s <> '' AND email = %s));
                """,
                [user_id, norm_email, norm_email],
            )
            return

        # Collect distinct phones from user_user and userProfile_userprofile
        raw_phones = []
        if user_row[1]:
            raw_phones.append(user_row[1])
        cursor.execute(
            'SELECT mobile_number FROM "userProfile_userprofile" WHERE user_id = %s LIMIT 1;',
            [user_id],
        )
        prof_row = cursor.fetchone()
        if prof_row and prof_row[0]:
            raw_phones.append(prof_row[0])

        phones = []
        seen = set()
        for raw in raw_phones:
            digits, last10 = normalize_phone(raw)
            if digits and digits not in seen:
                seen.add(digits)
                phones.append((digits, last10))

        if not phones:
            phones = [("", "")]

        for idx, (digits, last10) in enumerate(phones):
            email_for_row = norm_email if idx == 0 else ""
            canon_for_row = canon_email if idx == 0 else ""

            existing_id = None
            if email_for_row:
                cursor.execute(
                    "SELECT id FROM user_blockedcontact WHERE user_id = %s AND email = %s LIMIT 1;",
                    [user_id, email_for_row],
                )
                found = cursor.fetchone()
                if found:
                    existing_id = found[0]
            elif digits:
                cursor.execute(
                    "SELECT id FROM user_blockedcontact WHERE user_id = %s AND phone_number = %s LIMIT 1;",
                    [user_id, digits],
                )
                found = cursor.fetchone()
                if found:
                    existing_id = found[0]

            if existing_id:
                cursor.execute(
                    """
                    UPDATE user_blockedcontact
                    SET canonical_email = COALESCE(NULLIF(%s, ''), canonical_email),
                        phone_number = COALESCE(NULLIF(%s, ''), phone_number),
                        phone_last10 = COALESCE(NULLIF(%s, ''), phone_last10),
                        reason = COALESCE(NULLIF(%s, ''), reason),
                        is_active = true,
                        updated_at = NOW()
                    WHERE id = %s;
                    """,
                    [canon_for_row, digits, last10, reason_text, existing_id],
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO user_blockedcontact
                        (user_id, email, canonical_email, phone_number, phone_last10, reason, is_active, created_at, updated_at)
                    VALUES
                        (%s, NULLIF(%s, ''), NULLIF(%s, ''), NULLIF(%s, ''), NULLIF(%s, ''), %s, true, NOW(), NOW());
                    """,
                    [user_id, email_for_row, canon_for_row, digits, last10, reason_text],
                )

