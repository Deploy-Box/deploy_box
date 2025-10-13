from django.http import HttpRequest, JsonResponse
import requests
import os
from deploy_box_apis.models import APICredential

def generate(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    project_id = request.POST.get("project_id")
    if not project_id:
        return JsonResponse({"error": "Project ID is required, got: " + " ".join(list(request.POST.keys()))}, status=400)
    # Check if a credential already exists for this project
    existing_credential = APICredential.objects.filter(project_id=project_id).first()
    if existing_credential:
        return {
            "client_id": existing_credential.client_id,
            "client_secret_hint": existing_credential.client_secret_hint
        }


    os.environ.get('DEPLOY_BOX_API_BASE_URL').rstrip('/')

    url = f"{os.environ.get('DEPLOY_BOX_API_BASE_URL')}/api/client_self_service/generate"

    body = {
        "project_id": project_id
    }

    response = requests.post(url, json=body)

    if response.status_code != 200:
        raise Exception(f"Error generating API key: {response.text}")
    
    data = response.json()

    client_secret_hint = data['client_secret'][:4] + "..." + data['client_secret'][-4:]

    new_credential = APICredential(
        project_id=project_id,
        client_id=data['client_id'],
        client_secret=data['client_secret'],
        client_secret_hint=client_secret_hint
    )

    new_credential.save()
    
       

def revoke():
    pass

def regenerate():
    pass

# Create your views here.
def temporary(project_id: str):

# Mock API data for the marketplace
    available_apis = [
            {
                'id': 'geolocation-basic',
                'name': 'Geolocation API',
                'category': 'Location',
                'tier': 'Basic',
                'description': 'Get precise location data including coordinates, country, city, and timezone information',
                'price': 9.99,
                'features': [
                    'IP-based geolocation',
                    'Country and city detection',
                    'Timezone information',
                    '1,000 requests/month',
                    'JSON response format',
                    'Basic documentation'
                ],
                'icon': '🌍',
                'color': 'emerald',
                'popular': True,
                'endpoint': 'https://api.example.com/geolocation/v1',
                'response_time': '< 100ms'
            },
            {
                'id': 'weather-basic',
                'name': 'Weather API',
                'category': 'Weather',
                'tier': 'Basic',
                'description': 'Real-time weather data with current conditions and 5-day forecasts',
                'price': 14.99,
                'features': [
                    'Current weather conditions',
                    '5-day weather forecast',
                    'Temperature, humidity, wind data',
                    '2,000 requests/month',
                    'Multiple units support',
                    'Basic weather alerts'
                ],
                'icon': '🌤️',
                'color': 'emerald',
                'popular': True,
                'endpoint': 'https://api.example.com/weather/v1',
                'response_time': '< 200ms'
            },
            {
                'id': 'geolocation-premium',
                'name': 'Geolocation API - Premium',
                'category': 'Location',
                'tier': 'Premium',
                'description': 'Advanced geolocation with enhanced accuracy and additional data points',
                'price': 24.99,
                'features': [
                    'Everything in Basic',
                    'Enhanced accuracy',
                    'ISP and organization data',
                    '10,000 requests/month',
                    'Bulk geolocation',
                    'Advanced analytics',
                    'Priority support'
                ],
                'icon': '🌍',
                'color': 'amber',
                'popular': False,
                'endpoint': 'https://api.example.com/geolocation/v2',
                'response_time': '< 50ms'
            },
            {
                'id': 'weather-premium',
                'name': 'Weather API - Premium',
                'category': 'Weather',
                'tier': 'Premium',
                'description': 'Comprehensive weather data with extended forecasts and historical data',
                'price': 34.99,
                'features': [
                    'Everything in Basic',
                    'Extended 10-day forecast',
                    'Historical weather data',
                    '20,000 requests/month',
                    'Weather maps and radar',
                    'Severe weather alerts',
                    'Priority support'
                ],
                'icon': '🌤️',
                'color': 'amber',
                'popular': False,
                'endpoint': 'https://api.example.com/weather/v2',
                'response_time': '< 150ms'
            },
            {
                'id': 'currency-basic',
                'name': 'Currency Exchange API',
                'category': 'Finance',
                'tier': 'Basic',
                'description': 'Real-time currency exchange rates and conversion tools',
                'price': 12.99,
                'features': [
                    '170+ currency pairs',
                    'Real-time exchange rates',
                    'Historical rates',
                    '1,500 requests/month',
                    'JSON and XML formats',
                    'Basic conversion tools'
                ],
                'icon': '💰',
                'color': 'emerald',
                'popular': False,
                'endpoint': 'https://api.example.com/currency/v1',
                'response_time': '< 100ms'
            },
            {
                'id': 'email-validation-basic',
                'name': 'Email Validation API',
                'category': 'Validation',
                'tier': 'Basic',
                'description': 'Validate email addresses and check deliverability',
                'price': 7.99,
                'features': [
                    'Email format validation',
                    'Domain verification',
                    'Disposable email detection',
                    '2,500 requests/month',
                    'Bulk validation',
                    'Detailed response codes'
                ],
                'icon': '📧',
                'color': 'emerald',
                'popular': False,
                'endpoint': 'https://api.example.com/email/v1',
                'response_time': '< 80ms'
            },
            {
                'id': 'geolocation-pro',
                'name': 'Geolocation API - Pro',
                'category': 'Location',
                'tier': 'Pro',
                'description': 'Enterprise-grade geolocation with maximum accuracy and unlimited requests',
                'price': 49.99,
                'features': [
                    'Everything in Premium',
                    'Maximum accuracy',
                    'Unlimited requests',
                    'Custom data fields',
                    'White-label solution',
                    '24/7 priority support',
                    'SLA guarantee',
                    'Custom integrations'
                ],
                'icon': '🌍',
                'color': 'purple',
                'popular': False,
                'endpoint': 'https://api.example.com/geolocation/v3',
                'response_time': '< 25ms'
            },
            {
                'id': 'weather-pro',
                'name': 'Weather API - Pro',
                'category': 'Weather',
                'tier': 'Pro',
                'description': 'Enterprise weather solution with unlimited access and advanced features',
                'price': 69.99,
                'features': [
                    'Everything in Premium',
                    'Unlimited requests',
                    '30-day extended forecast',
                    'Weather modeling data',
                    'Custom weather alerts',
                    '24/7 priority support',
                    'SLA guarantee',
                    'Custom integrations'
                ],
                'icon': '🌤️',
                'color': 'purple',
                'popular': False,
                'endpoint': 'https://api.example.com/weather/v3',
                'response_time': '< 100ms'
            },
            {
                'id': 'ai-translation-basic',
                'name': 'AI Translation API',
                'category': 'AI',
                'tier': 'Basic',
                'description': 'Neural machine translation supporting 100+ languages',
                'price': 19.99,
                'features': [
                    '100+ language pairs',
                    'Neural translation',
                    'Context-aware translation',
                    '1,000 requests/month',
                    'Text and document translation',
                    'Basic language detection'
                ],
                'icon': '🤖',
                'color': 'emerald',
                'popular': False,
                'endpoint': 'https://api.example.com/translation/v1',
                'response_time': '< 500ms'
            },
            {
                'id': 'image-processing-basic',
                'name': 'Image Processing API',
                'category': 'Media',
                'tier': 'Basic',
                'description': 'AI-powered image processing, resizing, and optimization',
                'price': 16.99,
                'features': [
                    'Image resizing and cropping',
                    'Format conversion',
                    'Compression optimization',
                    '500 requests/month',
                    'Multiple output formats',
                    'Basic filters and effects'
                ],
                'icon': '🖼️',
                'color': 'emerald',
                'popular': False,
                'endpoint': 'https://api.example.com/image/v1',
                'response_time': '< 2s'
            }
        ]
    
    api_credential = APICredential.objects.filter(project_id=project_id).first()
    api_key = None
    if api_credential:
        api_key = {
            "client_id": api_credential.client_id,
            "client_secret_hint": api_credential.client_secret_hint
        }

    return {
        "available_apis": available_apis,
        "api_key": api_key
        }