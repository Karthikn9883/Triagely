// src/components/Pagination/Pagination.jsx

import React from "react";
import { FaChevronLeft, FaChevronRight } from "react-icons/fa";
import styles from "./Pagination.module.css";

export default function Pagination({ 
  currentPage, 
  totalPages, 
  onPageChange,
  className = ""
}) {
  // Debug logging
  console.log("Pagination props:", { currentPage, totalPages });
  
  // Temporarily always show pagination for debugging
  // if (totalPages <= 1) return null;

  const getVisiblePages = () => {
    const delta = 2; // Show 2 pages on each side of current page
    const range = [];
    const rangeWithDots = [];

    for (
      let i = Math.max(2, currentPage - delta);
      i <= Math.min(totalPages - 1, currentPage + delta);
      i++
    ) {
      range.push(i);
    }

    if (currentPage - delta > 2) {
      rangeWithDots.push(1, "...");
    } else {
      rangeWithDots.push(1);
    }

    rangeWithDots.push(...range);

    if (currentPage + delta < totalPages - 1) {
      rangeWithDots.push("...", totalPages);
    } else {
      rangeWithDots.push(totalPages);
    }

    return rangeWithDots;
  };

  const visiblePages = getVisiblePages();

  return (
    <div className={`${styles.pagination} ${className}`}>
      {/* Debug info */}
      <div style={{ fontSize: '12px', color: '#666', marginRight: '10px' }}>
        Page {currentPage} of {totalPages} (Debug)
      </div>
      
      {/* Previous button */}
      <button
        className={`${styles.pageButton} ${styles.arrowButton}`}
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        aria-label="Previous page"
      >
        <FaChevronLeft />
      </button>

      {/* Page numbers */}
      {visiblePages.map((page, index) => (
        <React.Fragment key={index}>
          {page === "..." ? (
            <span className={styles.dots}>...</span>
          ) : (
            <button
              className={`${styles.pageButton} ${
                page === currentPage ? styles.active : ""
              }`}
              onClick={() => onPageChange(page)}
              disabled={page === currentPage}
            >
              {page}
            </button>
          )}
        </React.Fragment>
      ))}

      {/* Next button */}
      <button
        className={`${styles.pageButton} ${styles.arrowButton}`}
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        aria-label="Next page"
      >
        <FaChevronRight />
      </button>
    </div>
  );
}