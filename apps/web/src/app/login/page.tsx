import { Card } from "@/components/Card";
import { LoginForm } from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-bold">登录</h1>
      <p className="text-sm text-gray-400">
        个人部署可在 API 设置 AUTH_PASSWORD 与 JWT_SECRET；默认用户邮箱见 DEFAULT_USER_EMAIL。
      </p>
      <Card title="获取访问令牌">
        <LoginForm />
      </Card>
    </div>
  );
}
