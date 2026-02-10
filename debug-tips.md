Docker Engine:
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ],
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "ip6tables": false
}

docker compose up -d --build
docker compose down
docker compose build --no-cache backend
docker compose up -d

docker compose run --rm -v "${PWD}:/workspace" -w /workspace backend python scripts/init_course_data.py

## Fork basics
已设置 upstream。按以下步骤操作：
步骤 1：Fork 仓库
在 Gitee 打开 https://gitee.com/naplus/aie55_llm5_learnhub
点击右上角的 "Fork" 按钮，fork 到你的账户
步骤 2：添加你的 fork 作为 origin
Fork 完成后，告诉我你的 Gitee 用户名，或直接提供 fork 仓库地址，我会帮你添加。
或者你可以手动运行：
git remote add origin git@gitee.com:你的用户名/aie55_llm5_learnhub.git
步骤 3：推送到你的 fork
git push -u origin feat/rag_pilot
步骤 4：创建 Pull Request
在 Gitee 上打开你的 fork 仓库
点击 "Pull Requests" → "新建 Pull Request"
选择从你的 feat/rag_pilot 分支到 naplus/aie55_llm5_learnhub 的相应分支
