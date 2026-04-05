export default function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null;

  const pages = [];
  for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {
    pages.push(i);
  }

  return (
    <div className="nb-pagination">
      <button
        className="nb-page-btn"
        onClick={() => onChange(page - 1)}
        disabled={page === 1}
      >
        &#8592; Prev
      </button>
      {page > 3 && (
        <>
          <button className="nb-page-btn" onClick={() => onChange(1)}>1</button>
          {page > 4 && <button className="nb-page-btn" disabled>···</button>}
        </>
      )}
      {pages.map((p) => (
        <button
          key={p}
          className={`nb-page-btn${p === page ? " active" : ""}`}
          onClick={() => onChange(p)}
        >
          {p}
        </button>
      ))}
      {page < totalPages - 2 && (
        <>
          {page < totalPages - 3 && <button className="nb-page-btn" disabled>···</button>}
          <button className="nb-page-btn" onClick={() => onChange(totalPages)}>{totalPages}</button>
        </>
      )}
      <button
        className="nb-page-btn"
        onClick={() => onChange(page + 1)}
        disabled={page === totalPages}
      >
        Next &#8594;
      </button>
    </div>
  );
}
