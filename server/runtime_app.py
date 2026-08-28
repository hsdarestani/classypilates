import os
import feedback_app as feedback
import class_language  # registers DE/EN class-language routes and payloads

app = feedback.app


@app.get('/api/capabilities')
def capabilities():
    return {
        'ok': True,
        'instant_email_notifications': bool(os.getenv('SMTP_HOST')),
        'sepa_provider_credentials': bool(os.getenv('STRIPE_SECRET_KEY') or os.getenv('SEPA_PROVIDER_KEY')),
        'booking_languages': ['de', 'en'],
        'class_languages': ['de', 'en'],
        'credit_packs': [1, 5, 10, 20, 30, 50],
        'class_recurrence': 'monthly',
        'monthly_memberships': True,
    }
