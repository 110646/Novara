from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import EmailCredit, Profile
from datetime import datetime

class PaymentsHistoryTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = Profile.objects.create(user=self.user)
        
        # Create some test email credits
        EmailCredit.objects.create(
            user=self.user,
            count=50,
            purchased_at=datetime.now()
        )
        EmailCredit.objects.create(
            user=self.user,
            count=100,
            purchased_at=datetime.now()
        )
    
    def test_payments_page_loads_with_payment_history(self):
        """Test that the payments page loads with payment history data"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('payments'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('payment_history', response.context)
        self.assertIn('latest_payment', response.context)
        self.assertIn('total_credits', response.context)
        self.assertIn('total_spent', response.context)
        self.assertEqual(len(response.context['payment_history']), 2)
        self.assertEqual(response.context['latest_payment'].count, 100)
        self.assertEqual(response.context['total_credits'], 150)
        self.assertEqual(response.context['total_spent'], 30.0)  # 150 * $0.20
    
    def test_payments_page_template_renders(self):
        """Test that the payments page template renders correctly"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('payments'))
        
        self.assertContains(response, 'Payments History')
        self.assertContains(response, 'Payment Summary')
        self.assertContains(response, 'Latest Purchase')
        self.assertContains(response, '100 emails purchased')
        self.assertContains(response, '$20.00')  # 100 * $0.20
        self.assertContains(response, '150')  # Total credits
        self.assertContains(response, '$30.00')  # Total spent
    
    def test_payments_page_with_no_history(self):
        """Test that the payments page handles no payment history correctly"""
        # Create a new user with no payment history
        new_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=new_user)
        
        self.client.login(username='newuser', password='testpass123')
        response = self.client.get(reverse('payments'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Payment History')
        self.assertContains(response, 'Buy Emails')
