import styles from './Footer.module.css';
import Link from 'next/link';

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.footerContent}`}>
        <div className={styles.left}>
          <div className={styles.logo}>hipoclypse</div>
          <div className={styles.copyright}>© 2024 hipoclipse Automation. All rights reserved.</div>
        </div>
        <div className={styles.right}>
          <Link href="#">Privacy Policy</Link>
          <Link href="#">Terms of Service</Link>
          <Link href="#">Status</Link>
          <Link href="#">Twitter</Link>
          <Link href="#">LinkedIn</Link>
        </div>
      </div>
    </footer>
  );
}
