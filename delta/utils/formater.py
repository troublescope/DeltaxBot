def format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours} jam, {minutes} menit, {seconds} detik"
    elif minutes > 0:
        return f"{minutes} menit, {seconds} detik"
    else:
        return f"{seconds} detik"
