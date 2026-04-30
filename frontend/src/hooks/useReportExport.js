/**
 * useReportExport.js — Custom Hook: Export report Excel file.
 *
 * Mọi API call qua services/api.js.
 */

import { useCallback, useState } from "react";
import { exportReport } from "../services/api";

export default function useReportExport() {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);

  const exportCafeReport = useCallback(async () => {
    setExporting(true);
    setExportError(null);

    try {
      const { blob, filename } = await exportReport();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err.message);
    } finally {
      setExporting(false);
    }
  }, []);

  return {
    exporting,
    exportError,
    exportCafeReport,
  };
}
