import Link from 'next/link';
import Button from '../ui/Button';
import styles from './Header.module.css';

export default function Header() {
  return (
    <header className={styles.header}>
      <div className={`container ${styles.headerContent}`}>
        <div className={styles.logo}>
          <Link href="/" className={styles.logoLink}>
            <span className={styles.logoBadge}>
              <img src="/logo.png" alt="hipoclipse logo" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '9999px' }} />
            </span>
            <span className={styles.logoText}>hipoclipse<span className={styles.logoDot}>.</span></span>
          </Link>
        </div>

        <nav className={styles.nav}>
          <Link href="#features" className={styles.navLink}>Features</Link>
          <Link href="#solutions" className={styles.navLink}>Solutions</Link>
          <Link href="#pricing" className={styles.navLink}>Pricing</Link>
          <Link href="#docs" className={styles.navLink}>Docs</Link>
        </nav>

        <div className={styles.actions}>
          <Link href="/dashboard">
            <Button variant="primary">Enter App</Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
