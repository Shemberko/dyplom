export type User = {
    id: string | null; 
    email: string | null;
};

export type UserAuthData = { 
    auth_date: string; 
    token: string;
    user: User;
};
