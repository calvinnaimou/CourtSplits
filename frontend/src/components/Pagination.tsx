interface Props {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
}

export default function Pagination({ page, totalPages, onChange }: Props) {
  if (totalPages <= 1) return null;
  return (
    <div className="pagination">
      <button disabled={page <= 1} onClick={() => onChange(page - 1)}>
        &larr; Previous
      </button>
      <span>
        Page {page} of {totalPages}
      </span>
      <button disabled={page >= totalPages} onClick={() => onChange(page + 1)}>
        Next &rarr;
      </button>
    </div>
  );
}
