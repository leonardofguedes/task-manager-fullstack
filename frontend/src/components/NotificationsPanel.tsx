import { useNotifications } from '../hooks/useNotifications'

export default function NotificationsPanel() {
  const { data, isPending, isError } = useNotifications()

  return (
    <aside aria-labelledby="notifications-title" className="rounded-xl bg-white p-4 ring-1 ring-slate-200">
      <h2 id="notifications-title" className="text-base font-semibold text-slate-900">
        Notifications
      </h2>
      {isPending && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
      {isError && <p className="mt-2 text-sm text-red-700">Could not load notifications.</p>}
      {data?.length === 0 && <p className="mt-2 text-sm text-slate-500">Nothing new.</p>}
      <ul className="mt-2 divide-y divide-slate-100">
        {data?.map((n) => (
          <li key={n.id} className="py-2">
            <p className="text-sm text-slate-800">
              <span
                className={`mr-2 inline-block h-2 w-2 rounded-full ${n.kind === 'overdue' ? 'bg-red-500' : 'bg-indigo-500'}`}
                aria-hidden="true"
              />
              {n.message}
            </p>
            <time dateTime={n.created_at} className="text-xs text-slate-500">
              {new Date(n.created_at).toLocaleString()}
            </time>
          </li>
        ))}
      </ul>
    </aside>
  )
}
