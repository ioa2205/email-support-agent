import re
import llm_service
import gmail_service
from database import get_db_connection

def handle_question(service, email):
    """Handles emails categorized as 'Question' using RAG."""
    print(f"Handling QUESTION from {email['from']}")
    question = gmail_service.clean_email_body(email['body'])
    answer = llm_service.get_rag_answer(question)
    
    if answer:
        reply_body = f"Hello,\n\nHere is an answer to your question:\n\n\"{answer}\"\n\nIf this doesn't help, please let us know.\n\nThank you,\nSupport Agent"
        gmail_service.send_reply(service, email['from'], f"Re: {email['subject']}", reply_body, email['threadId'])
    else:
        # Save as unhandled with high importance
        print("Could not find an answer. Saving to unhandled.")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO unhandled_emails (received_from, subject, body, category, importance)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (email['from'], email['subject'], email['body'], 'Question', 5)
        )
        conn.commit()
        cur.close()
        conn.close()

def handle_refund(service, email):
    """Handles emails categorized as 'Refund' with database logic."""
    print(f"Handling REFUND from {email['from']}")
    customer_email = re.search(r'<(.+?)>', email['from']).group(1) # Extract email from "Name <email@addr.com>"
    body = gmail_service.clean_email_body(email['body'])
    
    # Try to find an order ID
    match = re.search(r'order id\s*[:\s-]*([A-Z0-9]+)', body, re.IGNORECASE)
    if not match:
        match = re.search(r'\b(ORD\d+)\b', body, re.IGNORECASE)

    conn = get_db_connection()
    cur = conn.cursor()

    if not match:
        reply_body = "Hello,\n\nWe've received your refund request but could not find an order ID. Please reply to this email with your order ID.\n\nThank you,\nSupport Agent"
        gmail_service.send_reply(service, email['from'], f"Re: {email['subject']}", reply_body, email['threadId'])
    else:
        order_id = match.group(1).upper()
        cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
        order = cur.fetchone()

        if order:
            # Order found
            cur.execute("UPDATE orders SET status = 'refund_requested' WHERE order_id = %s", (order_id,))
            conn.commit()
            reply_body = f"Hello,\n\nYour refund request for order {order_id} has been received. It will be processed within 3 business days.\n\nThank you,\nSupport Agent"
            gmail_service.send_reply(service, email['from'], f"Re: {email['subject']}", reply_body, email['threadId'])
        else:
            # Order not found
            # Check if this is a reply to our "invalid ID" message
            if email.get('in_reply_to'):
                cur.execute(
                    """
                    INSERT INTO not_found_refund_requests (customer_email, invalid_order_id_attempted, full_email_body)
                    VALUES (%s, %s, %s)
                    """,
                    (customer_email, order_id, email['body'])
                )
                conn.commit()
                # Do not reply again to avoid loops. A human should check this table.
                print(f"Logged repeated invalid order ID attempt for {order_id}.")
            else:
                reply_body = f"Hello,\n\nWe could not find an order with the ID '{order_id}'. Please double-check the ID and reply to this email.\n\nThank you,\nSupport Agent"
                gmail_service.send_reply(service, email['from'], f"Re: {email['subject']}", reply_body, email['threadId'])
    
    cur.close()
    conn.close()


def handle_other(service, email):
    """Handles all other emails by assessing importance and saving."""
    print(f"Handling OTHER from {email['from']}")
    importance = llm_service.assess_importance(email['body'])
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO unhandled_emails (received_from, subject, body, category, importance)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (email['from'], email['subject'], email['body'], 'Other', importance)
    )
    conn.commit()
    cur.close()
    conn.close()

def process_email(account, email_summary):
    """Main pipeline for processing a single email."""
    service = gmail_service.get_gmail_service(account)
    email_details = gmail_service.get_email_details(service, email_summary['id'])

    clean_body = gmail_service.clean_email_body(email_details['body'])
    category = llm_service.categorize_email(clean_body)
    
    print(f"\n--- New Email ---")
    print(f"From: {email_details['from']}")
    print(f"Subject: {email_details['subject']}")
    print(f"Category: {category}")
    print("-------------------")

    if category == "Question":
        handle_question(service, email_details)
    elif category == "Refund":
        handle_refund(service, email_details)
    else: # Other
        handle_other(service, email_details)
        
    # Mark email as read after processing
    gmail_service.mark_as_read(service, email_details['id'])