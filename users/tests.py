from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import UserProfile


class UserAPITest(APITestCase):

    @classmethod
    def setUpTestData(cls):
        UserProfile.objects.create(full_name='Test User', email='test@example.com', role='Silver', is_active=True)
        UserProfile.objects.create(full_name='Inactive User', email='inactive@example.com', role='Silver', is_active=False)

    def test_get_users_list(self):
        url = reverse('user-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 2)

    def test_search_users(self):
        url = reverse('user-list-create') + '?search=Test'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_user_detail(self):
        user = UserProfile.objects.filter(full_name='Test User').first()
        url = reverse('user-detail', kwargs={'pk': user.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_update_user_status(self):
        user = UserProfile.objects.filter(full_name='Inactive User').first()
        url = reverse('user-status', kwargs={'pk': user.pk})
        response = self.client.patch(url, {'status': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_patch_update_user(self):
        user = UserProfile.objects.filter(full_name='Test User').first()
        url = reverse('user-detail', kwargs={'pk': user.pk})
        response = self.client.patch(url, {'plan': 'Gold', 'is_active': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.role, 'Gold')
        self.assertFalse(user.is_active)

    def test_create_user(self):
        url = reverse('user-list-create')
        payload = {
            'full_name': 'New User',
            'email': 'newuser@example.com',
            'role': 'Gold',
            'is_active': True
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserProfile.objects.filter(email='newuser@example.com').exists(), True)

