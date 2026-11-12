import { pageCount as countPages } from '../lib/pagination'

interface Props {
  page: number // 1-based
  pageSize: number
  total: number
  onPageChange: (page: number) => void
}

const buttonClass =
  'min-h-11 rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 ' +
  'hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50'

export default function Pagination({ page, pageSize, total, onPageChange }: Props) {
  const pageCount = countPages(total, pageSize)
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-3">
      <button
        type="button"
        className={buttonClass}
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </button>
      <span className="text-sm text-slate-600">
        Page {Math.min(page, pageCount)} of {pageCount} · {total} task{total === 1 ? '' : 's'}
      </span>
      <button
        type="button"
        className={buttonClass}
        disabled={page >= pageCount}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </button>
    </nav>
  )
}
