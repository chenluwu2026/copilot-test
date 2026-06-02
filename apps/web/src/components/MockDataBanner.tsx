import { api } from "@/lib/api";

export async function MockDataBanner() {
  let provider = "akshare";
  try {
    const info = await api.dataProviderInfo();
    provider = info.data_provider;
  } catch {
    return null;
  }
  if (provider !== "mock") return null;

  return (
    <div className="mb-4 rounded-lg border border-yellow-600/50 bg-yellow-900/20 px-4 py-2 text-center text-sm text-yellow-200">
      演示模式：当前为 <strong>mock</strong> 行情数据，非实盘行情。生产请设置{" "}
      <code className="text-yellow-100">DATA_PROVIDER=akshare</code> 并在{" "}
      <a href="/data" className="underline">
        数据中心
      </a>{" "}
      同步。
    </div>
  );
}
