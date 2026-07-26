import os
import uuid
from pathlib import Path
from app.core.config import settings

# Attempt to import Supabase, otherwise use local fallback
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = bool(settings.SUPABASE_URL and settings.SUPABASE_KEY and "your-supabase" not in settings.SUPABASE_URL)
except ImportError:
    SUPABASE_AVAILABLE = False

class StorageService:
    def __init__(self):
        self.supabase_client = None
        self.local_upload_dir = Path("uploads")
        self.local_upload_dir.mkdir(exist_ok=True)
        
        if SUPABASE_AVAILABLE:
            try:
                self.supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                print("Supabase Storage service initialized successfully.")
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase client: {e}. Using local storage fallback.")
                self.supabase_client = None
        else:
            print("Supabase credentials not configured. Using local storage fallback.")

    async def upload_file(self, file_content: bytes, file_name: str, content_type: str = "application/octet-stream") -> str:
        """
        Uploads a file to storage and returns the access URL.
        If Supabase is configured, uploads to Supabase Storage.
        Otherwise, writes to local 'uploads' directory.
        """
        # Generate a unique file name to avoid collisions
        unique_id = uuid.uuid4().hex
        ext = os.path.splitext(file_name)[1]
        unique_file_name = f"{unique_id}{ext}"

        if self.supabase_client:
            try:
                # Run the synchronous SDK call in a separate thread if necessary or directly
                # supabase-py uploads binary files easily
                bucket = settings.SUPABASE_BUCKET
                path_on_bucket = f"reports/{unique_file_name}"
                
                # Check bucket exists or attempt upload
                self.supabase_client.storage.from_(bucket).upload(
                    path=path_on_bucket,
                    file=file_content,
                    file_options={"content-type": content_type}
                )
                
                # Get public URL
                public_url = self.supabase_client.storage.from_(bucket).get_public_url(path_on_bucket)
                return public_url
            except Exception as e:
                print(f"Supabase upload failed: {e}. Falling back to local storage.")
                # Fall through to local upload

        # Local fallback
        local_path = self.local_upload_dir / unique_file_name
        with open(local_path, "wb") as f:
            f.write(file_content)
        
        # Return a local file access path or standard format
        return f"/uploads/{unique_file_name}"

    async def delete_file(self, file_url: str) -> bool:
        """Removes the file from storage."""
        if self.supabase_client and "supabase.co" in file_url:
            try:
                bucket = settings.SUPABASE_BUCKET
                # Extract path from URL
                # Example: https://xxx.supabase.co/storage/v1/object/public/pothys-reports/reports/file.pdf
                path_on_bucket = file_url.split(f"/{bucket}/")[-1]
                self.supabase_client.storage.from_(bucket).remove([path_on_bucket])
                return True
            except Exception as e:
                print(f"Failed to delete file from Supabase: {e}")
                return False
        
        # Local fallback
        if file_url.startswith("/uploads/"):
            file_name = file_url.split("/uploads/")[-1]
            local_path = self.local_upload_dir / file_name
            if local_path.exists():
                local_path.unlink()
                return True
        return False

storage_service = StorageService()
