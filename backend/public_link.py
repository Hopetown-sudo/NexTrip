from pyngrok import ngrok

# 为本地服务打开一个端口 (例如3001端口)
public_url = ngrok.connect(3000)

print(f"Public URL: {public_url}")

#ngrok http http://localhost:9000