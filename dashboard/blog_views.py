import json
from datetime import datetime, timezone
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import cloudinary.uploader


class BlogImageUploadAPI(APIView):
    """
    Direct image upload to Cloudinary for blog posts.
    Accepts multipart/form-data with 'image' or 'file'.
    Uploads to folder 'trackintake/blogs' and returns secure_url and metadata.
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        image_file = request.FILES.get('image') or request.FILES.get('file')
        if not image_file:
            return Response({"error": "No image file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            upload_result = cloudinary.uploader.upload(
                image_file,
                folder="trackintake/blogs",
                resource_type="image"
            )
            return Response({
                "success": True,
                "url": upload_result.get("secure_url"),
                "public_id": upload_result.get("public_id"),
                "format": upload_result.get("format"),
                "width": upload_result.get("width"),
                "height": upload_result.get("height"),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Cloudinary upload failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BlogListCreateAPI(APIView):
    """
    List blogs with search, author info, and pagination, or create a new blog.
    Direct raw SQL query against live features_blog table.
    """
    def get(self, request):
        search = request.query_params.get("search", "").strip()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        offset = (page - 1) * page_size
        where_clauses = ["1=1"]
        params = []

        if search:
            where_clauses.append("(b.title ILIKE %s OR b.content ILIKE %s OR u.full_name ILIKE %s)")
            wildcard = f"%{search}%"
            params.extend([wildcard, wildcard, wildcard])

        where_sql = " AND ".join(where_clauses)

        count_query = f"""
            SELECT COUNT(*) 
            FROM features_blog b
            LEFT JOIN user_user u ON b.author_id = u.id
            WHERE {where_sql};
        """

        list_query = f"""
            SELECT 
                b.id, b.title, b.content, b.image, b.created_at, b.updated_at,
                b.author_id, u.full_name as author_name, u.email as author_email
            FROM features_blog b
            LEFT JOIN user_user u ON b.author_id = u.id
            WHERE {where_sql}
            ORDER BY b.created_at DESC
            LIMIT %s OFFSET %s;
        """

        with connection.cursor() as cursor:
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            cursor.execute(list_query, params + [page_size, offset])
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "title": r[1],
                "content": r[2],
                "image": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "updated_at": r[5].isoformat() if r[5] else None,
                "author_id": r[6],
                "author_name": r[7] or "Admin",
                "author_email": r[8] or "",
            })

        total_pages = max(1, (total + page_size - 1) // page_size)
        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "results": results,
        })

    def post(self, request):
        data = request.data
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
        image = data.get("image", "").strip()
        author_id = data.get("author_id")

        if not title:
            return Response({"error": "Title is required"}, status=status.HTTP_400_BAD_REQUEST)

        now_utc = datetime.now(timezone.utc)

        # Fallback author_id to first admin or 1 if not provided
        if not author_id:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM user_user WHERE is_admin = true LIMIT 1;")
                admin_row = cursor.fetchone()
                author_id = admin_row[0] if admin_row else 1

        insert_sql = """
            INSERT INTO features_blog (title, content, image, created_at, updated_at, author_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        with connection.cursor() as cursor:
            cursor.execute(insert_sql, [title, content, image, now_utc, now_utc, author_id])
            new_id = cursor.fetchone()[0]

        return Response({
            "message": "Blog created successfully",
            "id": new_id
        }, status=status.HTTP_201_CREATED)


class BlogDetailAPI(APIView):
    """
    Retrieve, update or delete a blog post.
    """
    def get(self, request, pk):
        query = """
            SELECT 
                b.id, b.title, b.content, b.image, b.created_at, b.updated_at,
                b.author_id, u.full_name as author_name, u.email as author_email
            FROM features_blog b
            LEFT JOIN user_user u ON b.author_id = u.id
            WHERE b.id = %s;
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [pk])
            row = cursor.fetchone()

        if not row:
            return Response({"error": "Blog not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "image": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None,
            "author_id": row[6],
            "author_name": row[7] or "Admin",
            "author_email": row[8] or "",
        })

    def patch(self, request, pk):
        data = request.data
        updates = []
        params = []

        if "title" in data:
            updates.append("title = %s")
            params.append(data["title"])
        if "content" in data:
            updates.append("content = %s")
            params.append(data["content"])
        if "image" in data:
            updates.append("image = %s")
            params.append(data["image"])

        if not updates:
            return Response({"error": "No fields to update"}, status=status.HTTP_400_BAD_REQUEST)

        updates.append("updated_at = %s")
        params.append(datetime.now(timezone.utc))

        params.append(pk)
        update_sql = f"""
            UPDATE features_blog
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id;
        """
        with connection.cursor() as cursor:
            cursor.execute(update_sql, params)
            updated = cursor.fetchone()

        if not updated:
            return Response({"error": "Blog not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "Blog updated successfully"})

    def delete(self, request, pk):
        delete_sql = "DELETE FROM features_blog WHERE id = %s RETURNING id;"
        with connection.cursor() as cursor:
            cursor.execute(delete_sql, [pk])
            deleted = cursor.fetchone()

        if not deleted:
            return Response({"error": "Blog not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "Blog deleted successfully"})

