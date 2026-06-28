import json
from django.http import JsonResponse
from django.core.cache import caches

class RedisIdempotencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache = caches['default']

    def __call__(self, request):
        if request.method not in ["POST", "PATCH", "PUT"]:
            return self.get_response(request)

        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not idempotency_key:
            return self.get_response(request)

        cache_key = f"idempotency:{idempotency_key}"
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            if cached_data == "LOCK":
                return JsonResponse({"error": "Concurrent request flight in progress. Retry shortly."}, status=409)
            response_payload = json.loads(cached_data)
            return JsonResponse(response_payload['data'], status=response_payload['status'])

        self.cache.set(cache_key, "LOCK", timeout=120)
        response = self.get_response(request)

        if 200 <= response.status_code < 300:
            payload_to_cache = {
                "status": response.status_code,
                "data": json.loads(response.content.decode('utf-8')) if response.content else {}
            }
            self.cache.set(cache_key, json.dumps(payload_to_cache), timeout=86400)
        else:
            self.cache.delete(cache_key)

        return response
