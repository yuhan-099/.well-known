# Local Pentest Lab

一个只用于本机安全测试的故意脆弱 Web 靶场。它包含可复现的反射型 XSS、存储型 XSS、IDOR 和路径穿越示例，便于验证渗透测试工具是否能发现实际暴露面。

## 运行

```bash
cd local-pentest-lab
python3 app.py
```

服务固定绑定 `127.0.0.1:8000`。另开终端执行：

```bash
python3 verify.py
```

验证器只访问回环地址，不接受命令行目标参数。停止服务按 `Ctrl-C`。测试产生的 `lab.db` 已被 `.gitignore` 排除。

## 漏洞路由

| 示例 | 路由 | 现象 |
| --- | --- | --- |
| 反射型 XSS | `/search?q=...` | 查询内容原样写入 HTML |
| 存储型 XSS | `POST /comments` | 评论原样保存并渲染 |
| IDOR | `/users?id=2` | 未登录即可读取另一用户的敏感字段 |
| 路径穿越 | `/download?file=...` | 文件名未做规范化和目录限制 |

这些漏洞是教学数据，不代表真实系统风险。请只在本机或隔离实验网络中运行，禁止把服务端口映射到公网、共享主机或生产网络。

## GitHub 发布建议

可以公开仓库中的源码和文档，但不要提交 `lab.db`、真实凭据或生产配置。仓库描述应明确写上 `intentionally vulnerable / local training only`，并在 GitHub Actions 或 README 中保持默认绑定回环地址。

## 修复方向

生产代码应对 HTML 输出统一转义、对对象访问执行身份和权限校验、使用 `realpath` 加目录白名单限制下载路径，并将敏感字段从 API 响应中移除。修复后重新运行同样的验证用例，结果应全部为 `MISS`。
