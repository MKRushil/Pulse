from weaviate_service import query_pulse_vectors
from prompt_engine import build_prompt
from model_service import generate_response

def pulse_query(user_query):
    pulse_results = query_pulse_vectors(user_query)
    prompt = build_prompt(user_query, pulse_results)
    answer = generate_response(prompt)
    return {"reply": answer}
