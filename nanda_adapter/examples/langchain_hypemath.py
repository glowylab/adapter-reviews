#!/usr/bin/env python3
import os
from nanda_adapter import NANDA
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_anthropic import ChatAnthropic

def hype_math():
    """Create a LangChain-powered agent that encourages and promotes math education"""

    # Initialize the LLM
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307"
    )

    # Create a prompt template for math education
    prompt = PromptTemplate(
        input_variables=["message"],
        template="""You are a warm and encouraging mentor who is helping students learn math. Motivate them that studying math is exciting and applicable in many different fields of expertise. Use supportive language such as "you've got this", "curiosity", "dream", "dream", and "mission". Ask the questions if they would like to learn linear algebra and if they would like to go through a problem together.
        
        Student message: {message}\n\n
        
        Math advisor response:"""
    )

    # Create the chain
    chain = prompt | llm | StrOutputParser()

    def math_advisor(message_text: str) -> str:
        """Give students encouraging advice on selecting a major to study"""
        try:
            result = chain.invoke({"message": message_text})
            return result.strip()
        except Exception as e:
            print(f"Error in giving advice: {e}")
            return f"Oh no! {message_text}, I'm sorry I don't have advice."  # Fallback response

    return math_advisor

def main():
    """Main function to start the college major advice agent"""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set your ANTHROPIC_API_KEY environment variable")
        return

    # Create pirate improvement function
    pirate_logic = hype_math()

    # Initialize NANDA with pirate logic
    nanda = NANDA(pirate_logic)

    # Start the server
    print("Starting College Major Advice Agent with LangChain...")
    print("Giving college major advice!")

    domain = os.getenv("DOMAIN_NAME", "localhost")
    # port = int(os.getenv("PORT", "6000"))

    if domain != "localhost":
        # Production with SSL
        nanda.start_server_api(os.getenv("ANTHROPIC_API_KEY"), domain)
    else:
        # Development server
        nanda.start_server()
        
if __name__ == "__main__":
    main()