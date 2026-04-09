import { Navbar } from '@/components/soc/Navbar';
import { NetworkMap } from '@/components/soc/NetworkMap';
import { useLiveData } from '@/hooks/useLiveData';

export default function Network() {
  const { servers, algorithm, systemStatus, setAlgorithm, simulateFailure } = useLiveData();

  return (
    <div className="h-screen flex flex-col bg-background">
      <Navbar systemStatus={systemStatus} algorithm={algorithm} />
      <div className="flex-1 overflow-hidden">
        <NetworkMap
          servers={servers}
          algorithm={algorithm}
          onAlgorithmChange={setAlgorithm}
          onSimulateFailure={simulateFailure}
        />
      </div>
    </div>
  );
}
