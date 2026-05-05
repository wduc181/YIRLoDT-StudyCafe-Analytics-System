/**
 * App.jsx — Root Component, Routing/State Management.
 *
 * Quản lý app-level state: currentScreen, sessionData, gpsStatus.
 * Render màn hình tương ứng theo state (S1–S5).
 * Navigation map theo docs/ui_flow.md mục 6.
 * Không dùng localStorage/sessionStorage — chỉ React state (AGENTS.md rule 9.3).
 */

import { useState, useCallback } from "react";
import { SCREENS } from "./constants";
import useGps from "./hooks/useGps";
import useSession from "./hooks/useSession";
import useCafes from "./hooks/useCafes";
import useReportExport from "./hooks/useReportExport";

import HomeScreen from "./screens/HomeScreen";
import SessionActiveScreen from "./screens/SessionActiveScreen";
import ResultScreen from "./screens/ResultScreen";
import CafeListScreen from "./screens/CafeListScreen";
import SuggestCafeScreen from "./screens/SuggestCafeScreen";

/** Generate unique device ID per browser tab */
function getDeviceId() {
  return "device-" + Math.random().toString(36).substr(2, 9);
}

const DEVICE_ID = getDeviceId();

function App() {
  const [currentScreen, setCurrentScreen] = useState(SCREENS.HOME);

  const gps = useGps();
  const session = useSession();
  const cafes = useCafes();
  const reportExport = useReportExport();

  // ─── Navigation Handlers (ui_flow.md mục 6) ────────────

  /** S1 → S2: Bấm "Bắt đầu học" */
  const handleStartSession = useCallback(async () => {
    try {
      const data = await session.startSession(DEVICE_ID);
      gps.startTracking(data.session_id, DEVICE_ID);
      setCurrentScreen(SCREENS.SESSION_ACTIVE);
    } catch {
      // Error đã được set trong useSession hook
    }
  }, [session, gps]);

  /** S2 → S3: Bấm "Kết thúc" */
  const handleEndSession = useCallback(async () => {
    if (!session.sessionData?.sessionId) return;
    try {
      await session.endSession(session.sessionData.sessionId);
      gps.stopTracking();
      setCurrentScreen(SCREENS.RESULT);
    } catch {
      // Error đã được set trong useSession hook
    }
  }, [session, gps]);

  /** → S1: Về trang chủ */
  const handleGoHome = useCallback(() => {
    session.resetSession();
    setCurrentScreen(SCREENS.HOME);
  }, [session]);

  /** → S4: Xem danh sách quán */
  const handleGoToCafes = useCallback(() => {
    setCurrentScreen(SCREENS.CAFE_LIST);
  }, []);

  /** → S5: Đề xuất quán [Optional] */
  const handleGoToSuggest = useCallback(() => {
    setCurrentScreen(SCREENS.SUGGEST_CAFE);
  }, []);

  /** S5 → S4: Quay lại */
  const handleGoBackFromSuggest = useCallback(() => {
    setCurrentScreen(SCREENS.CAFE_LIST);
  }, []);

  // ─── Screen Rendering ──────────────────────────────────

  const renderScreen = () => {
    switch (currentScreen) {
      case SCREENS.HOME:
        return (
          <HomeScreen
            gpsStatus={gps.gpsStatus}
            gpsError={gps.error}
            onRequestGps={gps.requestPermission}
            onStartSession={handleStartSession}
            onGoToCafes={handleGoToCafes}
            loading={session.loading}
            error={session.error}
          />
        );

      case SCREENS.SESSION_ACTIVE:
        return (
          <SessionActiveScreen
            sessionData={session.sessionData}
            gpsStatus={gps.gpsStatus}
            gpsCount={gps.gpsCount}
            gpsError={gps.error}
            currentCafe={gps.currentCafe}
            scoringEligible={gps.scoringEligible}
            onEndSession={handleEndSession}
            loading={session.loading}
          />
        );

      case SCREENS.RESULT:
        return (
          <ResultScreen
            sessionData={session.sessionData}
            gpsCount={gps.gpsCount}
            onGoHome={handleGoHome}
            onGoToCafes={handleGoToCafes}
          />
        );

      case SCREENS.CAFE_LIST:
        return (
          <CafeListScreen
            cafes={cafes.cafes}
            pagination={cafes.pagination}
            loading={cafes.loading}
            error={cafes.error}
            onFetchCafes={cafes.fetchCafes}
            onGetCurrentPosition={gps.getCurrentPosition}
            onExportCafes={reportExport.exportCafeReport}
            exporting={reportExport.exporting}
            exportError={reportExport.exportError}
            onGoHome={handleGoHome}
            onGoToSuggest={handleGoToSuggest}
          />
        );

      case SCREENS.SUGGEST_CAFE:
        return <SuggestCafeScreen onGoBack={handleGoBackFromSuggest} />;

      default:
        return <HomeScreen />;
    }
  };

  return (
    <div className="min-h-screen bg-surface-dark">
      {renderScreen()}
    </div>
  );
}

export default App;
