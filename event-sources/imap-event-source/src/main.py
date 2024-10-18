import os, time, imapclient, logging, email, ssl, grpc, imap_proto_pb2_grpc, imap_proto_pb2
from email.header import decode_header
from concurrent import futures

logging.basicConfig(level=logging.INFO)

IMAP_SERVER = os.environ["IMAP_SERVER"]
EMAIL_ACCOUNT = os.environ["EMAIL_ACCOUNT"]
PASSWORD = os.environ["PASSWORD"]
SKIP_TLS_VERIFICATION = int(os.getenv("SKIP_TLS_VERIFICATION"), 0)
POLLING_FREQ = int(os.getenv("POLLING_FREQ", 5))


class EventingService(imap_proto_pb2_grpc.EventingServicer):
    def StartEventSource(self, request, context):
        logging.info(f"Received request to start event source: {request.name}")
        client = connect_to_imap()
        last_processed_id = get_last_processed_id()

        while True:
            unread_ids = get_unread_emails(client)
            unread_ids = [
                id
                for id in unread_ids
                if last_processed_id is None or int(id) > int(last_processed_id)
            ]

            if unread_ids:
                emails = fetch_emails(client, unread_ids)
                for email_info in emails:
                    event = imap_proto_pb2.Event(
                        name=request.name, payload=email_info["subject"].encode("utf-8")
                    )
                    yield event
                    last_processed_id = email_info["id"]
                    save_last_processed_id(last_processed_id)

                logging.info(
                    f"Processed {len(emails)} new email(s). Last one with id {last_processed_id}. Next iteration in {POLLING_FREQ}"
                )

            time.sleep(POLLING_FREQ)


# Connect to the IMAP server
def connect_to_imap():
    logging.info("Connecting to IMAP server...")
    if SKIP_TLS_VERIFICATION:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        client = imapclient.IMAPClient(IMAP_SERVER, ssl=True, ssl_context=ssl_context)
    else:
        client = imapclient.IMAPClient(IMAP_SERVER, ssl=True)
    client.login(EMAIL_ACCOUNT, PASSWORD)
    client.select_folder("INBOX")
    logging.info("Connected to IMAP server successfully.")
    return client


def get_unread_emails(client):
    """Retrieve the list of unread email IDs from the IMAP server."""
    unread_ids = client.search(["UNSEEN"])  # Fetch unread emails
    return unread_ids


def fetch_emails(client, email_ids):
    """Fetch the email details (subject) from the email IDs."""
    messages = client.fetch(email_ids, ["RFC822"])
    emails = []
    for email_id, message_data in messages.items():
        email_message = email.message_from_bytes(message_data[b"RFC822"])
        subject, encoding = decode_header(email_message["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")
        emails.append({"subject": subject, "id": email_id})
    return emails


def get_last_processed_id():
    """Get the last processed email ID from the state file."""
    if not os.path.exists("email_state.txt"):
        return None
    with open("email_state.txt", "r") as file:
        return file.read().strip()


def save_last_processed_id(email_id):
    """Save the last processed email ID to the state file."""
    with open("email_state.txt", "w") as file:
        file.write(str(email_id))


def serve():
    """Start the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    imap_proto_pb2_grpc.add_EventingServicer_to_server(EventingService(), server)
    server.add_insecure_port("[::]:50051")  # Expose port 50051
    print("Starting gRPC server on port 50051...")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    print("------------ Starting App ------------------")
    serve()
