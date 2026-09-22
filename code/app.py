import os
import base64
import traceback
import httpx
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 上限

# ============ 配置 ============
API_KEY = os.getenv("DASHSCOPE_API_KEY")
BASE_URL = os.getenv("DASHSCOPE_BASE_URL")
MODEL = os.getenv("DASHSCOPE_MODEL", "qwen3.5-plus")

if not API_KEY or not BASE_URL:
    raise RuntimeError("请在 .env 中配置 DASHSCOPE_API_KEY 和 DASHSCOPE_BASE_URL")

# ============ 启动自检 ============
print("=" * 60)
print(f"Model:    {MODEL}")
print(f"Base URL: {BASE_URL}")
try:
    r = httpx.get(BASE_URL, timeout=10.0)
    print(f"[自检] 网络可达，状态码: {r.status_code}")
except Exception as e:
    print(f"[自检] ❌ 网络不通: {type(e).__name__}: {e}")
print("=" * 60)

# ============ 关键：禁用连接复用，避免死连接 ============
http_client = httpx.Client(
    limits=httpx.Limits(max_keepalive_connections=0, max_connections=100),
    timeout=120.0,
)

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    http_client=http_client,
)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "model": MODEL})


@app.route('/analyze', methods=['POST'])
def analyze():
    # ---------- 入参校验 ----------
    data = request.get_json(silent=True)
    if not data or 'image_base64' not in data:
        return jsonify({"error": "没有收到图片", "type": "NO_IMAGE"}), 400

    img_b64 = data['image_base64']
    if img_b64.startswith("data:"):
        img_b64 = img_b64.split(",", 1)[1]

    img_size_kb = len(img_b64) * 3 // 4 // 1024  # base64 → 字节估算
    print(f"[请求] base64 长度: {len(img_b64)} 约 {img_size_kb} KB")

    if img_size_kb > 8 * 1024:
        return jsonify({
            "error": "图片太大了，请重新拍一张（建议小于 5MB）",
            "type": "IMAGE_TOO_LARGE"
        }), 413

    # ---------- 构造 prompt ----------
    prompt = (
        "你是一个老年人防诈骗助手。请分析这张保健品宣传图，"
        "判断是否存在伪科学话术、夸大疗效或诱导消费。"
        "如果有风险，用50字以内口语化提醒；如果正常，回复'未检测到明显风险'。"
    )

    # ---------- 调用大模型 ----------
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": prompt}
                ]
            }],
            max_tokens=300,
            temperature=0.3,
        )
        result = completion.choices[0].message.content
        print(f"[成功] {result[:80]}")
        return jsonify({"result": result})

    except Exception as e:
        err_name = type(e).__name__
        err_msg = str(e)
        print("=" * 60)
        print(f"❌ {err_name}: {err_msg}")
        traceback.print_exc()
        print("=" * 60)

        # ---------- 错误分类，给前端友好提示 ----------
        if "Authentication" in err_name:
            user_msg = "AI 服务认证失败，请联系管理员"
            err_type = "AUTH_ERROR"
        elif "Connection" in err_name or "RemoteProtocol" in err_msg:
            user_msg = "网络异常，请稍后重试"
            err_type = "NETWORK_ERROR"
        elif "Timeout" in err_name:
            user_msg = "AI 分析超时，请换张更清晰的图"
            err_type = "TIMEOUT"
        elif "BadRequest" in err_name:
            user_msg = "图片格式不支持，请重新拍摄"
            err_type = "BAD_IMAGE"
        else:
            user_msg = "分析失败，请重试"
            err_type = "UNKNOWN"

        return jsonify({
            "error": user_msg,
            "type": err_type,
            "detail": f"{err_name}: {err_msg[:200]}"
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)