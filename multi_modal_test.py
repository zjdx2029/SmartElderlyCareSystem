import base64
from openai import OpenAI

client = OpenAI(
    api_key="sk-ws-H.PIHHYMI.1Zgq.MEYCIQDl5-59a6wwnLVbFaoLFRE82ZRPSdvbGTXXUitB26fg1QIhALulRum3m9PHi04RR4B_NlvNzgB2nmENMqY6dpObpcJg",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

# 注意路径：代码在 code/ 文件夹里，图片在上一级 image/ 文件夹
image_b64 = encode_image("../image/test.jpg")

prompt = "你是一个老年人防诈骗助手。请分析这张保健品宣传图，判断是否存在伪科学话术、夸大疗效或诱导消费。如果有风险，用50字以内口语化提醒；如果正常，回复'未检测到明显风险'。"

try:
    completion = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
    )
    print("=== AI 分析结果 ===")
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"调用失败: {e}")