# causeway-storage-s3

S3-compatible storage adapter for Causeway. Works with AWS S3, Cloudflare R2, MinIO, Backblaze B2.

```python
from causeway import register
from causeway_storage_s3 import S3Storage

register(S3Storage(bucket="uploads", region="us-east-1"))
```
