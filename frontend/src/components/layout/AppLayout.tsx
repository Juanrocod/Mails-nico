import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import ErrorBoundary from './ErrorBoundary'
import { CicloProvider } from '../../contexts/CicloContext'

export default function AppLayout() {
  return (
    <CicloProvider>
      <div className="flex h-screen bg-background overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </CicloProvider>
  )
}
