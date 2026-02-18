import DigitalTwin from '@/components/digitial-twin-portfolio';

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 to-gray-100">
      
      {/* Content wrapper that grows */}
      <div className="flex-grow">
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-4xl font-bold text-center text-gray-800 mb-2">
              AI in Production
            </h1>

            <p className="text-center text-gray-600 mb-8">
              Powered by Amazon Web Services and OpenAI Digital Twin to the cloud
            </p>

            <div className="min-h-[1000px]">
              <DigitalTwin />
            </div>
          </div>
        </div>
      </div>

      {/* Footer stays inside gradient + bottom aligned */}
      <footer className="py-4 text-center text-sm text-gray-500">
        <p>Darin's Digital Twin</p>
      </footer>

    </main>
  );
}
