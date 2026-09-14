from django.http import JsonResponse

def health_check(request):
    """
    Health check endpoint to verify the application's status.
    Returns a JSON response indicating the health of the application.
    """
    return JsonResponse({"status": "ok"})