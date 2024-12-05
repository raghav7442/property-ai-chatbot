import logging

# Configure logging
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def handle_exceptions(func):
    """
    A decorator to handle exceptions in functions.
    - Logs the error.
    - Returns a default response or re-raises the error.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as ve:
            logging.error(f"ValueError in {func.__name__}: {ve}")
            return {"error": str(ve)}, 400
        except KeyError as ke:
            logging.error(f"KeyError in {func.__name__}: {ke}")
            return {"error": f"Missing key: {str(ke)}"}, 400
        except Exception as e:
            logging.error(f"Exception in {func.__name__}: {e}", exc_info=True)
            return {"error": "An unexpected error occurred."}, 500
    return wrapper
