#!/usr/bin/env python3
import os
from nanda_adapter import NANDA
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_anthropic import ChatAnthropic

AGENT_NAME = "Linear Algebra"

def create_linearalgebra():
    """Create a LangChain-powered agent that explains core linear algebra ideas."""

    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307",
        temperature=0.2,
    )

    prompt = PromptTemplate(
        input_variables=["message"],
        template=(
            "You are a precise but friendly Linear Algebra tutor. "
            "Explain clearly and concisely. When helpful, demonstrate a small example "
            "with Gaussian elimination.\n\n"
            "Cover: matrix & vector algebra, Gaussian elimination, vector spaces, "
            "linear independence, and eigenvectors. Only include math that is relevant "
            "to the student's request.\n\n"
            "Student message: {message}\n\n"
            "Tutor:"
        ),
    )

    chain = prompt | llm | StrOutputParser()

    def linear_advisor(message_text: str) -> str:
        """Return a short, clear explanation for a linear algebra question."""
        if message_text.strip().lower() in {"whoami", "id"}:
            return AGENT_NAME
        try:
            result = chain.invoke({"message": message_text})
            return result.strip()
        except Exception as e:
            return f"Sorry—linear algebra tutor hit an error: {e}"

    return linear_advisor

def main():
    """Start the Linear Algebra Agent (LangChain) behind a NANDA server."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set your ANTHROPIC_API_KEY environment variable")
        return

    linear_logic = create_linearalgebra()
    nanda = NANDA(linear_logic)

    print("Starting Linear Algebra Agent with LangChain...")

    domain = os.getenv("DOMAIN_NAME", "localhost")
    if domain != "localhost":
        nanda.start_server_api(os.getenv("ANTHROPIC_API_KEY"), domain)
    else:
        nanda.start_server()

if __name__ == "__main__":
    key = os.getenv("ANTHROPIC_API_KEY")
    # debbienanda.duckdns.org
    domain = os.getenv("DOMAIN_NAME")  
    assert key and domain, "Set ANTHROPIC_API_KEY and DOMAIN_NAME env vars first."
    NANDA(create_linearalgebra()).start_server_api(key, domain)

# if __name__ == "__main__":
#     main()
