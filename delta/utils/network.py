import aiohttp


async def upload_cdn(file_path):
    url = "https://cdn.maelyn.tech/api/upload"
    form = aiohttp.FormData()
    # Open the file so it remains open during the upload
    f = open(file_path, "rb")
    form.add_field(
        "file",
        f,
        filename=file_path.split("/")[-1],
        content_type="application/octet-stream",
    )

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=form) as response:
                if response.status == 200:
                    data = await response.json()
                    url_value = data["data"].get("url")
                    size_value = data["data"].get("size")
                    expired_value = data["data"].get("expired")

                    return url_value, size_value, expired_value

                else:
                    text = await response.text()
                    return text
        except Exception as e:
            return str(e)
        finally:
            # Close the file after the upload is complete
            f.close()
