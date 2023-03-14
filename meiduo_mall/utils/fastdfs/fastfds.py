from fdfs_client.client import Fdfs_client, get_tracker_conf


track_config = get_tracker_conf('utils/fastdfs/client.conf')
client = Fdfs_client(track_config)
client.upload_by_filename('C:/Users/liu/Desktop/1.webp')

