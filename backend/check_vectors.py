"""Check vector count in Qdrant."""
from vector_db.client import get_qdrant_client


def main():
    """Check total vectors."""
    client = get_qdrant_client()
    client.connect()

    # List all collections
    collections = client.client.get_collections()
    print(f'Available collections: {[c.name for c in collections.collections]}')

    # Check the grace collection
    if collections.collections:
        collection_name = collections.collections[0].name
        info = client.client.get_collection(collection_name)
        print(f'\nCollection: {collection_name}')
        print(f'Points count: {info.points_count}')
        print(f'Vector size: {info.config.params.vectors.size}')
        print(f'Distance metric: {info.config.params.vectors.distance}')


if __name__ == '__main__':
    main()
