import os
import azure.storage.blob as azblob

azure_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
azure_container_name = "images"
blob_service_client = azblob.BlobServiceClient.from_connection_string(azure_connection_string)
container_client = blob_service_client.get_container_client(azure_container_name)