# -*- coding: utf-8 -*-
"""
This script fetches all data from the 'TCMCase' class in Weaviate
and dumps it into a JSON file.
"""
import os
import json
import weaviate
from weaviate.exceptions import WeaviateQueryException

def get_weaviate_client():
    """
    Creates and returns a Weaviate client using configuration from environment variables
    or default values.
    """
    url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    api_key = os.getenv("WEAVIATE_API_KEY", "key-admin")

    try:
        client = weaviate.Client(
            url=url,
            additional_headers={"Authorization": f"Bearer {api_key}"},
            timeout_config=(5, 60),
        )
        # Test connection
        client.schema.get()
        print(f"Successfully connected to Weaviate at {url}")
        return client
    except Exception as e:
        print(f"Failed to connect to Weaviate: {e}")
        raise

def dump_all_tcm_cases(client: weaviate.Client, class_name: str, output_path: str):
    """
    Fetches all objects from a given class in Weaviate and writes them to a JSON file.
    Handles pagination to retrieve all objects.
    """
    print(f"Starting data dump for class: '{class_name}'...")
    
    all_objects = []
    cursor = None
    
    # Get all properties from the schema to fetch everything
    try:
        schema = client.schema.get(class_name)
        properties = [prop['name'] for prop in schema['properties']]
    except WeaviateQueryException as e:
        print(f"Error getting schema for class '{class_name}': {e}")
        print("Please ensure the class exists and the schema is accessible.")
        return

    while True:
        try:
            query = (
                client.query.get(class_name, properties)
                .with_additional(["id"])
                .with_limit(100)
            )
            
            if cursor:
                result = query.with_after(cursor).do()
            else:
                result = query.do()

            data = result["data"]["Get"][class_name]

            if not data:
                print("No more data to fetch.")
                break

            all_objects.extend(data)
            cursor = data[-1]["_additional"]["id"]
            print(f"Fetched {len(data)} objects. Total fetched: {len(all_objects)}")

        except WeaviateQueryException as e:
            print(f"An error occurred during query: {e}")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break

    print(f"Total objects retrieved: {len(all_objects)}")

    # Write to JSON file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_objects, f, ensure_ascii=False, indent=4)
        print(f"Successfully dumped all data to {output_path}")
    except IOError as e:
        print(f"Failed to write to file {output_path}: {e}")


if __name__ == "__main__":
    CLASS_NAME = "TCMCase"
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_FILE = os.path.join(script_dir, "tcm_cases_dump.json")

    try:
        weaviate_client = get_weaviate_client()
        dump_all_tcm_cases(weaviate_client, CLASS_NAME, OUTPUT_FILE)
    except Exception as e:
        print(f"An error occurred during the process: {e}")

