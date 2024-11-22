import io
from io import BytesIO


def dos2unix(content: bytes) -> BytesIO:
    output: BytesIO = BytesIO()
    for line in content.splitlines():
        output.write(line + b"\n")
    output.seek(0)
    return output
