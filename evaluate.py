from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama

# Initialize the evaluator LLM
llm_evaluator = ChatOllama(model="llama3", temperature=0)

faithfulness_prompt = PromptTemplate(
    template="""You are an expert evaluator. Assess if the following Answer is faithful to the Context.
An answer is faithful if it contains only information present in the Context and does not hallucinate new facts.

Context: {context}
Answer: {answer}

Provide a binary score 'yes' or 'no' indicating if the answer is faithful to the context. Provide ONLY 'yes' or 'no'.""",
    input_variables=["context", "answer"],
)

answer_relevance_prompt = PromptTemplate(
    template="""You are an expert evaluator. Assess if the following Answer addresses the user's Question.
An answer is relevant if it directly answers the user's question.

Question: {question}
Answer: {answer}

Provide a binary score 'yes' or 'no' indicating if the answer is relevant to the question. Provide ONLY 'yes' or 'no'.""",
    input_variables=["question", "answer"],
)

def evaluate_response(question, context, answer):
    """
    Evaluates faithfulness and answer relevance.
    Returns a dictionary of scores.
    """
    if not context.strip():
        # If no context was used, faithfulness is not applicable
        faithfulness_score = "N/A"
    else:
        faithfulness_chain = faithfulness_prompt | llm_evaluator
        try:
            faithfulness_score = faithfulness_chain.invoke({
                "context": context,
                "answer": answer
            }).content.strip().lower()
        except Exception:
            faithfulness_score = "error"

    relevance_chain = answer_relevance_prompt | llm_evaluator
    try:
        relevance_score = relevance_chain.invoke({
            "question": question,
            "answer": answer
        }).content.strip().lower()
    except Exception:
        relevance_score = "error"

    return {
        "faithfulness": "yes" in faithfulness_score if faithfulness_score not in ["N/A", "error"] else faithfulness_score,
        "answer_relevance": "yes" in relevance_score if relevance_score != "error" else "error"
    }
