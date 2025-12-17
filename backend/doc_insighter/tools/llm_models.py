from crewai import LLM
import os
from dotenv import load_dotenv
load_dotenv()

# from langchain_openai import AzureChatOpenAI 



# azure_llm = AzureChatOpenAI(
#     azure_deployment="gpt-4o",
#     api_key=os.getenv("AZURE_OPENAI_API_KEY"), # type: ignore
#     azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     api_version="2024-02-15-preview",
# )

llm = LLM(model="azure/gpt-4o",
          api_key=os.getenv("AZURE_API_KEY"),
          api_base=os.getenv("AZURE_API_BASE"),
          api_version=os.getenv("AZURE_API_VERSION"),
          temperature=0.5,
          )

# Sample code to test llm ############################################

from crewai import Agent, Task, Crew

data_analyst = Agent(
    role='Graph Database Analyst',
    goal='Analyze and query graph data stored in Neo4j database',
    backstory="""You are an expert graph database analyst with deep knowledge of 
    Cypher query language and Neo4j operations. You can efficiently retrieve, 
    analyze, and interpret complex graph data patterns.""",
    # tools=[neo4j_tool],
    llm=llm,
    verbose=True
)

# Example tasks
def create_sample_data_task():
    return Task(
        description="""Create sample data in the Neo4j database. Create nodes for:
        - 3 Person nodes with properties: name, age, city
        - 2 Company nodes with properties: name, industry
        - Create relationships between people and companies (WORKS_FOR)
        - Create relationships between people (KNOWS)
        
        Use appropriate Cypher CREATE statements.""",
        agent=data_analyst,
        expected_output="Confirmation that sample data has been created successfully"
    )

def run_crew():
    crew = Crew(
        agents=[data_analyst],
        tasks=[
            create_sample_data_task(),
            # query_data_task(),
            # analyze_patterns_task()
        ],
        verbose=True
    )
    
    result = crew.kickoff()
    return result

# if __name__ == "__main__":
#     # Make sure to set your Neo4j credentials in environment variables
#     # or modify the NEO4J_* variables above
    
#     print("Starting CrewAI with Neo4j integration...")
#     result = run_crew()
#     print("\nFinal Result:")
#     print(result)

# from sklearn.feature_extraction.text import CountVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# import re

# def sentence_relevance(s1: str, s2: str, threshold: float = 0.6) -> bool:
#     # Preprocess sentences (lowercase, remove punctuation)
#     def clean_text(text):
#         return re.sub(r'[^\w\s]', '', text.lower())
    
#     s1_clean, s2_clean = clean_text(s1), clean_text(s2)
    
#     # ----- 1. Common word overlap -----
#     words1, words2 = set(s1_clean.split()), set(s2_clean.split())
#     common_word_score = len(words1 & words2) / max(len(words1 | words2), 1)
    
#     # ----- 2. Semantic similarity (cosine on Bag-of-Words) -----
#     vectorizer = CountVectorizer().fit([s1_clean, s2_clean])
#     vectors = vectorizer.transform([s1_clean, s2_clean])
#     semantic_score = cosine_similarity(vectors[0], vectors[1])[0][0] # type:ignore
    
#     # ----- Hybrid score -----
#     hybrid_score = (common_word_score + semantic_score) / 2
    
#     return hybrid_score >= threshold

# # Example usage
# print(sentence_relevance("store repository structure", "store structure", 0.8))  
