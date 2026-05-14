import os
import unittest
from dotenv import load_dotenv

try:
    from backend.app.tools import getTools
except ImportError:
    from app.tools import getTools

class AgentToolsIntegrationTest(unittest.TestCase):
    """
    getTools로 꺼내온 도구들을 LangChain Agent에 물려서 잘 사용하는지 확인하는 테스트입니다.
    """

    @classmethod
    def setUpClass(cls):
        # .env 파일 로드
        load_dotenv()
        cls.api_key = os.getenv("OPENAI_API_KEY")
        if not cls.api_key:
            raise unittest.SkipTest("OPENAI_API_KEY가 설정되지 않아 테스트를 건너뜁니다.")

    def test_agent_uses_tools(self):
        try:
            from langchain_openai import ChatOpenAI
            from langchain.agents import create_tool_calling_agent, AgentExecutor
            from langchain_core.prompts import ChatPromptTemplate
        except ImportError:
            raise unittest.SkipTest("langchain 관련 패키지가 없어 테스트를 건너뜁니다.")

        # 1. getTools()로 도구들 꺼내오기
        tools = getTools()
        self.assertTrue(len(tools) > 0, "도구가 하나 이상 로드되어야 합니다.")

        tool_names = [t.name for t in tools]
        print(f"\n[AgentTest] 로드된 도구: {tool_names}")

        # 2. env로 직접 코딩해서 client(LLM) 만들기
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_DESC_MODEL", "solar-pro"),
            temperature=0,
            api_key=self.api_key,
            base_url=os.getenv("OPENAI_BASE_URL")
        )

        # 3. Agent에 들어갈 프롬프트 준비
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Use the provided tools to answer the user's question."),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        # 4. Agent 만들고 tool 물리기
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        # 5. 다 잘 쓰는지 확인하기 (특허 검색 또는 개수 확인 질의)
        query = "가상현실과 관련된 특허를 찾아줘."
        
        result = agent_executor.invoke({"input": query})
        
        print("\n[AgentTest] 질의:", query)
        print("[AgentTest] Agent 응답:", result["output"])
        
        self.assertIsNotNone(result["output"])
        self.assertIsInstance(result["output"], str)
        self.assertTrue(len(result["output"]) > 0)

if __name__ == "__main__":
    unittest.main()
