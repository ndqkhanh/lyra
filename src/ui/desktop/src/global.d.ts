export {}

interface LyraAPI {
  getApiUrl: () => Promise<string>
  fetch: (urlPath: string, options?: RequestInit) => Promise<IpcResponse>
  connectSSE: (
    ssePath: string,
    callbacks: {
      onData?: (path: string, data: string) => void
      onEvent?: (path: string, event: string) => void
      onError?: (path: string, error: string) => void
    },
    body?: string,
  ) => () => void
}

interface IpcResponse {
  ok: boolean
  status: number
  body: string
}

declare global {
  interface Window {
    lyraAPI: LyraAPI
  }
}
