import { Outlet, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { C } from "../styles/tokens";

export default function MinimalLayout() {
  const location = useLocation();
  return (
    <div style={{ minHeight: "100vh", background: C.bgPrimary }}>
      <AnimatePresence mode="wait">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
        >
          <Outlet />
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
