import aiohttp


async def http_request(url, method="GET", **kwargs):
    """
    Simple async HTTP request function that passes kwargs directly to aiohttp.

    Args:
        url: Target URL endpoint
        method: HTTP method (GET, POST, PUT, etc.)
        **kwargs: Any parameters supported by aiohttp.ClientSession.request
                  (params, json, headers, timeout, etc.)

    Returns:
        Response as JSON if possible, otherwise as text
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, url, **kwargs) as response:
                # Try to get JSON, fall back to text
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    return await response.text()
        except Exception as e:
            return f"Error: {str(e)}"
