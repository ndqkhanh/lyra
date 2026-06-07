import { contextBridge, ipcRenderer } from 'electron'

export interface IpcResponse {
  ok: boolean
  status: number
  body: string
}

const api = {
  /** Get the API base URL (from env or default). */
  getApiUrl: (): Promise<string> => ipcRenderer.invoke('lyra:api-url'),

  /** Fetch via main process proxy (avoids CORS). */
  fetch: (urlPath: string, options?: RequestInit): Promise<IpcResponse> =>
    ipcRenderer.invoke('lyra:fetch', urlPath, options),

  /** Connect to an SSE stream. Returns an unsubscribe function. */
  connectSSE: (
    ssePath: string,
    callbacks: {
      onData?: (path: string, data: string) => void
      onEvent?: (path: string, event: string) => void
      onError?: (path: string, error: string) => void
    },
  ): (() => void) => {
    const dataHandler = (_event: Electron.IpcRendererEvent, path: string, data: string) => {
      if (path === ssePath) callbacks.onData?.(path, data)
    }
    const eventHandler = (_event: Electron.IpcRendererEvent, path: string, name: string) => {
      if (path === ssePath) callbacks.onEvent?.(path, name)
    }
    const errorHandler = (_event: Electron.IpcRendererEvent, path: string, error: string) => {
      if (path === ssePath) callbacks.onError?.(path, error)
    }

    ipcRenderer.on('sse:data', dataHandler)
    ipcRenderer.on('sse:event', eventHandler)
    ipcRenderer.on('sse:error', errorHandler)

    ipcRenderer.invoke('lyra:sse-connect', ssePath)

    return () => {
      ipcRenderer.removeListener('sse:data', dataHandler)
      ipcRenderer.removeListener('sse:event', eventHandler)
      ipcRenderer.removeListener('sse:error', errorHandler)
    }
  },
}

contextBridge.exposeInMainWorld('lyraAPI', api)
