# AIMS 界面静态预览

无需启动后端，用浏览器直接打开：

```bash
# 方式 1：直接打开文件
xdg-open preview/aims-preview.html   # Linux
open preview/aims-preview.html     # macOS

# 方式 2：本地静态服务（推荐，避免部分浏览器限制）
cd preview && python3 -m http.server 8080
# 浏览器访问 http://localhost:8080/aims-preview.html
```

`aims-preview.html` 展示当前 8 个核心页面的布局与示意数据（深色主题），与 Next.js 产品界面一致。

若要操作真实数据，请按根目录 `README.md` 启动 API + Web。
