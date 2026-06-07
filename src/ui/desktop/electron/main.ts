import { app, BrowserWindow, ipcMain } from 'electron'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))

let mainWindow: BrowserWindow | null = null

const isDev = process.env['NODE_ENV'] === 'development' || !app.isPackaged

const VITE_DEV_SERVER_URL = 'http://127.0.0.1:5173'
const API_BASE_URL = process.env['LYRA_API_URL'] || 'http://127.0.0.1:8580'

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 900,
    minHeight: 600,
    title: 'Lyra',
    backgroundColor: '#0f1117',
    show: false,
    webPreferences: {
      preload: join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  if (isDev) {
    mainWindow.loadURL(VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// ─── IPC Handlers ─────────────────────────────────────────────

ipcMain.handle('lyra:api-url', () => API_BASE_URL)

// Proxy API requests from renderer through main process
ipcMain.handle('lyra:fetch', async (_event, urlPath: string, options?: RequestInit) => {
  const url = `${API_BASE_URL}${urlPath}`
  try {
    const resp = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers as Record<string, string>),
      },
    })
    const text = await resp.text()
    return {
      ok: resp.ok,
      status: resp.status,
      body: text,
    }
  } catch (error) {
    return {
      ok: false,
      status: 0,
      body: (error as Error).message,
    }
  }
})

// SSE stream proxy: main process fetches SSE, forwards chunks to renderer
ipcMain.handle('lyra:sse-connect', async (event, ssePath: string) => {
  const url = `${API_BASE_URL}${ssePath}`
  const abortController = new AbortController()
  const win = BrowserWindow.fromWebContents(event.sender)

  let closed = false
  event.sender.on('destroyed', () => {
    closed = true
    abortController.abort()
  })

  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
      signal: abortController.signal,
    })

    if (!resp.ok || !resp.body) {
      win?.webContents.send('sse:error', ssePath, `HTTP ${resp.status}`)
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (!closed) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          win?.webContents.send('sse:data', ssePath, data)
        } else if (line.startsWith('event: ')) {
          win?.webContents.send('sse:event', ssePath, line.slice(7))
        }
      }
    }
  } catch (error) {
    if (!closed) {
      win?.webContents.send('sse:error', ssePath, (error as Error).message)
    }
  }
})

// ─── App Lifecycle ────────────────────────────────────────────

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow()
  }
})
