import React, { useEffect } from 'react';
import { getTasks } from '@/api/taskService';

const TasksPage: React.FC = () => {
  useEffect(() => {
    const load = async () => {
      try {
        await getTasks();
      } catch {}
    };
    load();
  }, []);

  return <div>Tasks</div>;
};

export default TasksPage;