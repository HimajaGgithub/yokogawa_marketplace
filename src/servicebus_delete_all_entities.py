import dotenv
import os
from azure.servicebus.management import ServiceBusAdministrationClient

dotenv.load_dotenv()
conn = os.getenv('NAMESPACE_CONNECTION_STR')

try:
    x = input("> Delete all topics and subscriptions (yes or no):")
    if x != "yes":
        print("Exiting...")
        exit(0)
    servicebus_admin_client = ServiceBusAdministrationClient.from_connection_string(conn)
    topics = servicebus_admin_client.list_topics()
    for topic in topics:
        print(f"Topic Name: {topic.name}")
        for sub in servicebus_admin_client.list_subscriptions(topic_name=topic.name):
            print("Deleting subscription", sub.name)
            servicebus_admin_client.delete_subscription(topic.name, sub.name)
        print("Deleting topic", topic.name)
        servicebus_admin_client.delete_topic(topic_name=topic.name)
except Exception as e:
    print(f"Error deleting topic: {e}")
finally:
    # Close the client when done
    if 'servicebus_admin_client' in locals() and servicebus_admin_client:
        servicebus_admin_client.close()
