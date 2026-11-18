import PrintLetter from "../../../../../features/jobs/print-letter";

export default async function PrintPage({ params }: { params: Promise<{ letterId: string }> }) {
  const { letterId } = await params;
  return <PrintLetter id={letterId} />;
}
