import { Outlet } from 'react-router-dom'
import { Footer } from './Footer'
import { TopNav } from './TopNav'

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-on-background">
      <TopNav />
      <Outlet />
      <Footer />
    </div>
  )
}
