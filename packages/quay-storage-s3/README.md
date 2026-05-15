# quay-storage-s3

S3-compatible storage adapter for Quay. Works with AWS S3, Cloudflare R2, MinIO, Backblaze B2.

```python
from quay import register
from quay_storage_s3 import S3Storage

register(S3Storage(bucket="uploads", region="us-east-1"))
```
