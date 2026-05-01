import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import Overview from "./pages/Overview";
import UserAnalytics from "./pages/UserAnalytics";
import ContentPerformance from "./pages/ContentPerformance";
import Monetisation from "./pages/Monetisation";
import Retention from "./pages/Retention";
import LanguageAnalysis from "./pages/LanguageAnalysis";
import ABTest from "./pages/ABTest";
import SQLWorkbench from "./pages/SQLWorkbench";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="users" element={<UserAnalytics />} />
          <Route path="content" element={<ContentPerformance />} />
          <Route path="monetisation" element={<Monetisation />} />
          <Route path="retention" element={<Retention />} />
          <Route path="language" element={<LanguageAnalysis />} />
          <Route path="ab-test" element={<ABTest />} />
          <Route path="sql" element={<SQLWorkbench />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
