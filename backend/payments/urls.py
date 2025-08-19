from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'subscription-plans', views.SubscriptionPlanViewSet, basename='subscriptionplan')
router.register(r'subscriptions', views.SubscriptionViewSet, basename='subscription')
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'payment-methods', views.PaymentMethodViewSet, basename='paymentmethod')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Stripe integration
    path('create-payment-intent/', views.CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('confirm-payment/', views.ConfirmPaymentView.as_view(), name='confirm-payment'),
    path('stripe-webhook/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
    
    # Subscription management
    path('subscribe/', views.SubscribeView.as_view(), name='subscribe'),
    path('cancel-subscription/', views.CancelSubscriptionView.as_view(), name='cancel-subscription'),
    
    # Payment methods
    path('add-payment-method/', views.AddPaymentMethodView.as_view(), name='add-payment-method'),
    path('payment-methods/<int:method_id>/set-default/', views.SetDefaultPaymentMethodView.as_view(), name='set-default-payment-method'),
    
    # Invoices and billing
    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
    path('invoices/<int:invoice_id>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    
    # Discount codes
    path('validate-discount/', views.ValidateDiscountView.as_view(), name='validate-discount'),
] 